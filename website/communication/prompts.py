CALL_DIRECTION_PROMPTS = {
    "inbound": lambda user: f"""
Hey! This is {user.first_name} with YD Cocktails.

We're reaching out to you about your bartending service inquiry. We tried giving you a call but couldn't connect.

Please give us a call back when you have a chance or let us know how we can help you.

Si prefiere español déjenos saber!
""",
    "outbound": lambda user: f"""
Hey! This is {user.first_name} with YD Cocktails.

We saw that you recently called us but weren't able to reach someone. We're here to help with your bartending service inquiry.

Feel free to text us back or call when it's convenient.

Si prefiere español déjenos saber!
"""
}