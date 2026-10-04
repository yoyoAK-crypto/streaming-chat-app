import httpx

base = "http://127.0.0.1:8000" # The address of your running server. Saved in a variable so you don't retype it.
creds = {"username": "youssef", "password": "secret123"} # "Credentials": a dictionary with the username and password you're testing with. It's reused in the first two requests.

r = httpx.post(base + "/signup", json=creds) # sends an HTTP POST to http://127.0.0.1:8000/signup. json=creds turns the dict into a JSON body, which your UserCreate schema then validates.
print("signup:", r.status_code, r.json())

r = httpx.post(base + "/login", json=creds)
# finds the user, runs verify_password to compare your typed password with the stored hash, and if it matches, builds a JWT.
print("login:", r.status_code, r.json())

r = httpx.post(base + "/login", json={"username": "youssef", "password": "wrong"})
# verify_password fails, so the server raises HTTPException(401).
print("bad login:", r.status_code, r.json())