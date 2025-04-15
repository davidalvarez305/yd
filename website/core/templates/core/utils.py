def is_mobile(user_agent):
    return any(keyword in user_agent for keyword in ["Mobile", "Android", "iPhone", "iPad", "iPod"])