import hashlib
import time
import json
import logging
from typing import Optional, Dict, Any, Literal
from decimal import Decimal
from datetime import datetime
import requests
from requests.exceptions import Timeout, RequestException
from enum import Enum


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PaymentStatus(str, Enum):
    """Статусы платежей"""
    PENDING = "pending"
    WAITING = "waiting"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    ERROR = "error"
    CANCELLED = "cancelled"


class ClickPaymentProvider:
    """
    Универсальный класс для работы с Click.uz Payment API
    
    Использование:
        provider = ClickPaymentProvider(
            merchant_id="12345",
            merchant_service_id="67890",
            merchant_user_id="11111",
            secret_key="your_secret_key"
        )
    """
    
    API_ENDPOINT = "https://api.click.uz/v2/merchant"
    PAYMENT_URL = "https://my.click.uz/pay/"
    
    def __init__(
        self,
        merchant_id: str,
        merchant_service_id: str,
        merchant_user_id: str,
        secret_key: str,
        timeout: int = 30,  # 30 секунд таймаут
        max_retries: int = 0  # Не повторять автоматически
    ):
        self.merchant_id = merchant_id
        self.merchant_service_id = merchant_service_id
        self.merchant_user_id = merchant_user_id
        self.secret_key = secret_key
        self.timeout = timeout
        self.max_retries = max_retries
        
        logger.info(f"ClickPaymentProvider initialized: merchant_id={merchant_id}, service_id={merchant_service_id}, timeout={timeout}s")
    
    def _generate_auth_token(self, timestamp: int) -> str:
        """Генерация токена авторизации"""
        string = f"{timestamp}{self.secret_key}"
        token = hashlib.sha1(string.encode('utf-8')).hexdigest()
        logger.debug(f"Generated auth token for timestamp={timestamp}")
        return token
    
    def _get_headers(self) -> Dict[str, str]:
        """Получение заголовков для API запросов"""
        timestamp = int(time.time())
        token = self._generate_auth_token(timestamp)
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Auth': f'{self.merchant_user_id}:{token}:{timestamp}'
        }
        
        logger.debug(f"Generated headers with timestamp={timestamp}")
        return headers
    
    def _make_request(
        self,
        method: Literal["GET", "POST", "DELETE"],
        endpoint: str,
        data: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """Универсальный метод для API запросов с retry логикой"""
        url = f"{self.API_ENDPOINT}{endpoint}"
        headers = self._get_headers()
        
        logger.info(f"📤 {method} {endpoint}")
        if data:
            logger.debug(f"Request data: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        start_time = time.time()
        
        logger.info(f"Request URL: {url}, data: {json.dumps(data, ensure_ascii=False, indent=2)}, headers: {json.dumps(headers, ensure_ascii=False, indent=2)}")
        try:
            if method == "GET":
                response = requests.get(url, headers=headers) #timeout=self.timeout)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers) #timeout=self.timeout)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers) #timeout=self.timeout)
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ Request completed in {elapsed_time:.2f}s | Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"📥 Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error: {str(e)}")
                    return {
                        'error': -500,
                        'error_note': f'Invalid JSON response: {response.text[:200]}'
                    }
            else:
                error_text = response.text[:500]
                logger.error(f"❌ HTTP {response.status_code}: {error_text}")
                return {
                    'error': -1 * response.status_code,
                    'error_note': f'HTTP error [{response.status_code}]',
                    'response_text': error_text
                }
                
        except Timeout as e:
            elapsed_time = time.time() - start_time
            logger.error(f"⏱️ TIMEOUT after {elapsed_time:.2f}s | {method} {endpoint}")
            
            # Retry логика для таймаута (если включено)
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                logger.warning(f"🔄 Retry {retry_count + 1}/{self.max_retries} after {wait_time}s...")
                time.sleep(wait_time)
                return self._make_request(method, endpoint, data, retry_count + 1)
            
            return {
                'error': -408,
                'error_note': f'Request timeout after {elapsed_time:.2f}s',
                'timeout': True,
                'suggestion': 'Check if request was processed on Click side'
            }
            
        except RequestException as e:
            elapsed_time = time.time() - start_time
            logger.error(f"❌ Request error after {elapsed_time:.2f}s: {type(e).__name__} - {str(e)}")
            
            # Retry для сетевых ошибок
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                logger.warning(f"🔄 Retry {retry_count + 1}/{self.max_retries} after {wait_time}s...")
                time.sleep(wait_time)
                return self._make_request(method, endpoint, data, retry_count + 1)
            
            return {
                'error': -1,
                'error_note': f'Request exception: {str(e)}',
                'exception_type': type(e).__name__
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.exception(f"💥 Unexpected error after {elapsed_time:.2f}s")
            return {
                'error': -500,
                'error_note': f'Unexpected exception: {str(e)}',
                'exception_type': type(e).__name__
            }
    
    # ============= INVOICE МЕТОДЫ =============
    
    def create_invoice(
        self,
        amount: float,
        phone_number: str,
        merchant_trans_id: str
    ) -> Dict[str, Any]:
        """
        Создание инвойса для оплаты через телефон
        
        Args:
            amount: Сумма платежа
            phone_number: Номер телефона (998XXXXXXXXX)
            merchant_trans_id: ID транзакции мерчанта
        """
        logger.info(f"💳 Creating invoice | amount={amount} | phone={phone_number} | trans_id={merchant_trans_id}")
        
        data = {
            'service_id': self.merchant_service_id,
            'amount': float(amount),
            'phone_number': phone_number,
            'merchant_trans_id': merchant_trans_id
        }
        
        result = self._make_request("POST", "/invoice/create", data)
        
        if result.get('error_code') == 0:
            invoice_id = result.get('invoice_id')
            logger.info(f"✅ Invoice created successfully: invoice_id={invoice_id}")
        elif result.get('timeout'):
            logger.warning(f"⚠️ Invoice creation TIMEOUT! trans_id={merchant_trans_id}")
            logger.warning(f"💡 Suggestion: Check invoice status manually or wait for webhook")
        else:
            error_code = result.get('error_code', result.get('error'))
            error_note = result.get('error_note', '')
            logger.error(f"❌ Invoice creation failed: error={error_code}, note={error_note}")
        
        return result
    
    def check_invoice_status(self, invoice_id: str) -> Dict[str, Any]:
        """
        Проверка статуса инвойса
        
        Args:
            invoice_id: ID инвойса Click
        """
        logger.info(f"🔍 Checking invoice status: invoice_id={invoice_id}")
        
        endpoint = f"/invoice/status/{self.merchant_service_id}/{invoice_id}"
        result = self._make_request("GET", endpoint)
        
        if result.get('status') is not None:
            status = result['status']
            status_note = result.get('status_note', '')
            
            if status > 0:
                logger.info(f"✅ Invoice {invoice_id} CONFIRMED | status={status}")
            elif status == -99:
                logger.warning(f"⚠️ Invoice {invoice_id} REJECTED | status={status}")
            elif status < 0:
                logger.error(f"❌ Invoice {invoice_id} ERROR | status={status} | {status_note}")
            else:
                logger.info(f"⏳ Invoice {invoice_id} PENDING | status={status}")
        
        return result
    
    # ============= CARD TOKEN МЕТОДЫ =============
    
    def create_card_token(
        self,
        card_number: str,
        expire_date: str,
        temporary: int = 0
    ) -> Dict[str, Any]:
        """
        Создание токена карты
        
        Args:
            card_number: Номер карты (16 цифр)
            expire_date: Срок действия (MMYY)
            temporary: 0 - постоянный токен, 1 - временный
        """
        masked_card = f"{card_number[:4]}****{card_number[-4:]}"
        logger.info(f"💳 Creating card token | card={masked_card} | expire={expire_date} | temporary={temporary}")
        
        data = {
            'service_id': self.merchant_service_id,
            'card_number': card_number,
            'expire_date': expire_date,
            'temporary': temporary
        }
        
        result = self._make_request("POST", "/card_token/request", data)
        
        if result.get('error_code') == 0:
            card_token = result.get('card_token')
            phone_number = result.get('phone_number', 'N/A')
            logger.info(f"✅ Card token created | token={card_token} | phone={phone_number}")
        elif result.get('timeout'):
            logger.warning(f"⚠️ Card token creation TIMEOUT! card={masked_card}")
            logger.warning(f"💡 Wait for SMS code, then verify manually")
        else:
            error_code = result.get('error_code', result.get('error'))
            error_note = result.get('error_note', '')
            logger.error(f"❌ Card token creation failed: error={error_code}, note={error_note}")
        
        return result
    
    def verify_card_token(
        self,
        card_token: str,
        sms_code: str
    ) -> Dict[str, Any]:
        """
        Верификация токена карты с помощью SMS кода
        
        Args:
            card_token: Токен карты
            sms_code: SMS код подтверждения
        """
        logger.info(f"🔐 Verifying card token | token={card_token} | sms=***")
        
        data = {
            'service_id': self.merchant_service_id,
            'card_token': card_token,
            'sms_code': sms_code
        }
        
        result = self._make_request("POST", "/card_token/verify", data)
        
        if result.get('error_code') == 0:
            logger.info(f"✅ Card token verified successfully")
        else:
            error_code = result.get('error_code', result.get('error'))
            error_note = result.get('error_note', '')
            logger.error(f"❌ Card token verification failed: error={error_code}, note={error_note}")
        
        return result
    
    def payment_with_token(
        self,
        card_token: str,
        amount: float,
        merchant_trans_id: str
    ) -> Dict[str, Any]:
        """
        Оплата с использованием токена карты
        
        Args:
            card_token: Токен карты
            amount: Сумма платежа
            merchant_trans_id: ID транзакции мерчанта
        """
        logger.info(f"💰 Payment with token | token={card_token} | amount={amount} | trans_id={merchant_trans_id}")
        
        data = {
            'service_id': self.merchant_service_id,
            'card_token': card_token,
            'amount': float(amount),
            'transaction_parameter': merchant_trans_id
        }
        
        result = self._make_request("POST", "/card_token/payment", data)
        
        if result.get('error_code') == 0:
            payment_id = result.get('payment_id')
            logger.info(f"✅ Payment successful | payment_id={payment_id}")
        elif result.get('timeout'):
            logger.warning(f"⚠️ Payment TIMEOUT! trans_id={merchant_trans_id}")
            logger.warning(f"💡 Check payment status or wait for webhook")
        else:
            error_code = result.get('error_code', result.get('error'))
            error_note = result.get('error_note', '')
            logger.error(f"❌ Payment failed: error={error_code}, note={error_note}")
        
        return result
    
    def delete_card_token(self, card_token: str) -> Dict[str, Any]:
        """
        Удаление токена карты
        
        Args:
            card_token: Токен карты для удаления
        """
        logger.info(f"🗑️ Deleting card token: {card_token}")
        
        endpoint = f"/card_token/{self.merchant_service_id}/{card_token}"
        result = self._make_request("DELETE", endpoint)
        
        if result.get('error_code') == 0:
            logger.info(f"✅ Card token deleted successfully")
        else:
            error_code = result.get('error_code', result.get('error'))
            error_note = result.get('error_note', '')
            logger.error(f"❌ Card token deletion failed: error={error_code}, note={error_note}")
        
        return result
    
    # ============= WEBHOOK МЕТОДЫ =============
    
    def verify_webhook_signature(
        self,
        click_trans_id: str,
        service_id: str,
        order_id: str,
        merchant_prepare_id: str,
        amount: str,
        action: str,
        sign_time: str,
        sign_string: str
    ) -> bool:
        """
        Проверка подписи webhook запроса от Click
        
        Returns:
            True если подпись валидна, False в противном случае
        """
        expected_string = (
            f"{click_trans_id}{service_id}{self.secret_key}"
            f"{order_id}{merchant_prepare_id}{amount}{action}{sign_time}"
        )
        expected_signature = hashlib.md5(expected_string.encode('utf-8')).hexdigest()
        
        is_valid = expected_signature == sign_string
        
        if is_valid:
            logger.info(f"✅ Webhook signature valid | order_id={order_id}")
        else:
            logger.error(f"❌ Webhook signature INVALID | order_id={order_id}")
            logger.debug(f"Expected: {expected_signature}")
            logger.debug(f"Got: {sign_string}")
        
        return is_valid
    
    def validate_webhook_data(
        self,
        webhook_data: Dict[str, Any],
        expected_amount: float,
        payment_status: str
    ) -> Dict[str, Any]:
        """
        Валидация данных webhook
        
        Returns:
            Dict с ключами 'error' и 'error_note'
        """
        order_id = webhook_data.get('merchant_trans_id', 'unknown')
        action = webhook_data.get('action', 'unknown')
        action_name = 'PREPARE' if action == '0' else 'COMPLETE' if action == '1' else 'UNKNOWN'
        
        logger.info(f"🔍 Validating webhook | order_id={order_id} | action={action_name}")
        logger.debug(f"Webhook data: {json.dumps(webhook_data, ensure_ascii=False, indent=2)}")
        
        required_fields = [
            'click_trans_id', 'service_id', 'click_paydoc_id',
            'amount', 'action', 'error', 'error_note',
            'sign_time', 'sign_string', 'merchant_trans_id'
        ]
        
        # Проверка наличия обязательных полей
        missing_fields = [field for field in required_fields if field not in webhook_data]
        if missing_fields:
            logger.error(f"❌ Missing fields: {missing_fields}")
            return {
                'error': '-8',
                'error_note': 'Error in request from Click'
            }
        
        if action == '1' and 'merchant_prepare_id' not in webhook_data:
            logger.error("❌ Missing merchant_prepare_id for COMPLETE")
            return {
                'error': '-8',
                'error_note': 'Error in request from Click'
            }
        
        # Проверка подписи
        merchant_prepare_id = webhook_data.get('merchant_prepare_id', '')
        if not self.verify_webhook_signature(
            webhook_data['click_trans_id'],
            webhook_data['service_id'],
            webhook_data['merchant_trans_id'],
            merchant_prepare_id,
            webhook_data['amount'],
            webhook_data['action'],
            webhook_data['sign_time'],
            webhook_data['sign_string']
        ):
            return {
                'error': '-1',
                'error_note': 'SIGN CHECK FAILED!'
            }
        
        # Проверка action
        if action not in ['0', '1']:
            logger.error(f"❌ Invalid action: {action}")
            return {
                'error': '-3',
                'error_note': 'Action not found'
            }
        
        # Проверка суммы
        webhook_amount = float(webhook_data['amount'])
        if abs(webhook_amount - float(expected_amount)) > 0.01:
            logger.error(f"❌ Amount mismatch | expected={expected_amount}, got={webhook_amount}")
            return {
                'error': '-2',
                'error_note': 'Incorrect parameter amount'
            }
        
        # Проверка статуса оплаты
        if payment_status == PaymentStatus.CONFIRMED:
            logger.warning(f"⚠️ Already paid | order_id={order_id}")
            return {
                'error': '-4',
                'error_note': 'Already paid'
            }
        
        # Проверка для complete
        if action == '1':
            if order_id != merchant_prepare_id:
                logger.error(f"❌ ID mismatch | order={order_id}, prepare={merchant_prepare_id}")
                return {
                    'error': '-6',
                    'error_note': 'Transaction not found'
                }
        
        # Проверка на отмену
        error = int(webhook_data.get('error', 0))
        if payment_status == PaymentStatus.REJECTED or error < 0:
            logger.warning(f"⚠️ Transaction cancelled | order_id={order_id}, error={error}")
            return {
                'error': '-9',
                'error_note': 'Transaction cancelled'
            }
        
        logger.info(f"✅ Webhook validation successful | order_id={order_id}")
        return {
            'error': '0',
            'error_note': 'Success'
        }
    
    # ============= PAYMENT FORM МЕТОДЫ =============
    
    def generate_payment_form_data(
        self,
        amount: float,
        transaction_id: str,
        description: str = "",
        email: str = "",
        return_url: str = "/"
    ) -> Dict[str, str]:
        """
        Генерация данных для формы оплаты Click
        
        Returns:
            Словарь с данными для формы (hidden inputs)
        """
        logger.info(f"📝 Generating payment form | amount={amount} | trans_id={transaction_id}")
        
        sign_time = datetime.now().strftime('%Y-%m-%d')
        sign_string = self._generate_form_signature(
            sign_time, transaction_id, amount
        )
        
        form_data = {
            'action_url': self.PAYMENT_URL,
            'MERCHANT_TRANS_AMOUNT': str(amount),
            'MERCHANT_ID': self.merchant_id,
            'MERCHANT_USER_ID': self.merchant_user_id,
            'MERCHANT_SERVICE_ID': self.merchant_service_id,
            'MERCHANT_TRANS_ID': transaction_id,
            'MERCHANT_TRANS_NOTE': description,
            'MERCHANT_USER_EMAIL': email,
            'SIGN_TIME': sign_time,
            'SIGN_STRING': sign_string,
            'RETURN_URL': return_url
        }
        
        logger.debug(f"Form data: {json.dumps(form_data, ensure_ascii=False, indent=2)}")
        return form_data
    
    def _generate_form_signature(
        self,
        sign_time: str,
        transaction_id: str,
        amount: float
    ) -> str:
        """Генерация подписи для формы оплаты"""
        string = (
            f"{sign_time}{self.secret_key}{self.merchant_service_id}"
            f"{transaction_id}{amount}"
        )
        signature = hashlib.md5(string.encode('utf-8')).hexdigest()
        logger.debug(f"Generated form signature for trans_id={transaction_id}")
        return signature