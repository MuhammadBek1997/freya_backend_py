#!/usr/bin/env python3
"""
Script to examine the existing PostgreSQL database structure
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def connect_to_db():
    """Connect to PostgreSQL database"""
    try:
        # Database connection parameters
        conn = psycopg2.connect(
            host="c3mvmsjsgbq96j.cluster-czz5s0kz4scl.eu-west-1.rds.amazonaws.com",
            database="d7cho3buhj3j6g",
            user="u82hhsnrq03vdb",
            password="p894645a6da7b84f388ce131c8306b8bf2c5c3a5c7b32d2e5cd60987b1c644d1f",
            port="5432"
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def get_all_tables(conn):
    """Get all tables in the database"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        cursor.close()
        return [table['table_name'] for table in tables]
    except Exception as e:
        print(f"Error getting tables: {e}")
        return []

def get_table_structure(conn, table_name):
    """Get the structure of a specific table"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns 
            WHERE table_name = %s 
            AND table_schema = 'public'
            ORDER BY ordinal_position;
        """, (table_name,))
        columns = cursor.fetchall()
        cursor.close()
        return columns
    except Exception as e:
        print(f"Error getting table structure for {table_name}: {e}")
        return []

def get_foreign_keys(conn, table_name):
    """Get foreign key constraints for a table"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = %s
                AND tc.table_schema = 'public';
        """, (table_name,))
        foreign_keys = cursor.fetchall()
        cursor.close()
        return foreign_keys
    except Exception as e:
        print(f"Error getting foreign keys for {table_name}: {e}")
        return []

def main():
    """Main function to examine database structure"""
    print("Connecting to PostgreSQL database...")
    conn = connect_to_db()
    
    if not conn:
        print("Failed to connect to database")
        return
    
    print("Connected successfully!")
    print("\n" + "="*80)
    print("DATABASE STRUCTURE ANALYSIS")
    print("="*80)
    
    # Get all tables
    tables = get_all_tables(conn)
    print(f"\nFound {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")
    
    print("\n" + "="*80)
    print("DETAILED TABLE STRUCTURES")
    print("="*80)
    
    # Examine each table
    for table_name in tables:
        print(f"\n📋 TABLE: {table_name.upper()}")
        print("-" * 60)
        
        # Get table structure
        columns = get_table_structure(conn, table_name)
        if columns:
            print("Columns:")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                data_type = col['data_type']
                if col['character_maximum_length']:
                    data_type += f"({col['character_maximum_length']})"
                elif col['numeric_precision']:
                    data_type += f"({col['numeric_precision']}"
                    if col['numeric_scale']:
                        data_type += f",{col['numeric_scale']}"
                    data_type += ")"
                
                print(f"  • {col['column_name']:<25} {data_type:<20} {nullable}{default}")
        
        # Get foreign keys
        foreign_keys = get_foreign_keys(conn, table_name)
        if foreign_keys:
            print("\nForeign Keys:")
            for fk in foreign_keys:
                print(f"  • {fk['column_name']} → {fk['foreign_table_name']}.{fk['foreign_column_name']}")
        
        print()
    
    conn.close()
    print("Database examination completed!")

if __name__ == "__main__":
    main()