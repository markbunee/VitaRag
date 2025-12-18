from service.auth_to.password import get_password_hash
import sys

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_password.py <password>")
        sys.exit(1)

    password = sys.argv[1]
    hashed_password = get_password_hash(password)
    print(f"Hashed password: {hashed_password}")
