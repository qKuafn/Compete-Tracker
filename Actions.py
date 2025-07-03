from main import main
from tokens import *

if __name__ == "__main__":
    ensure_token()
    ensure_token("second")
    main()
    kill_token()