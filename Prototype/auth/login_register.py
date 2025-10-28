from surreal_conn import SurrealConn

class AuthService:
    def __init__(self, surreal_conn: SurrealConn):
        self.surreal_conn = surreal_conn.getting_db("test")
        
    async def login_user(self, email: str, password: str):
        try:
            userAuth = await self.surreal_conn.db.query("SELECT id, username FROM User WHERE email = $email;",
                { email })
            if not userAuth:
                return None
            username = userAuth[0]['username']
            isValid = await self.surreal_conn.db.query("RETURN fn::verification($username, $password);",
                {
                  username,
                  password,
                })
            if not isValid:
                return None
            token = await self.surreal_conn.db.query("RETURN fn::jwt::create($username);",
                { username })
            print(token)
            return {"token": token, "username": username, "id": userAuth[0]['id']}
        except Exception as e:
            print(f"Error during login: {e}")
            return None