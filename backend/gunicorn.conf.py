import os

bind = "0.0.0.0:" + os.getenv("PORT", "8000")
workers = 3
