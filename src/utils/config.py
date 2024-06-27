import configparser

config = configparser.RawConfigParser()
config.read("config.ini")

mongodb_srv: str = config["MONGODB"]["srv"]
mongodb_cli: str = config["MONGODB"]["cli"]
