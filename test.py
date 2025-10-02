import os


print("Environment Variables:")
for key, value in os.environ.items():
    print(f"{key}: {value}")
