import configparser

config = configparser.RawConfigParser()
config.read("config.ini")

mongodb_cli: str = config["MONGODB"]["cli"]
