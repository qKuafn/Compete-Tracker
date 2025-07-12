from main import main
from tokens import ensure_token, kill_token

if __name__ == "__main__":
    ensure_token()
    ensure_token("second")
    main(Actions=True)
    kill_token()
    kill_token("second")