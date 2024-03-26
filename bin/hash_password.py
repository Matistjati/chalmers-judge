from django.contrib.auth.hashers import make_password

raw_password = input("give password")
hashed_password = make_password(raw_password)

print(f"hashed: {hashed_password}")
