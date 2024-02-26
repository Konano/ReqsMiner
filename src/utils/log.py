import logging
import traceback

from rich.logging import RichHandler

FORMAT = "%(message)s"
logging.basicConfig(level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("rich")


def error_handler(e: Exception) -> None:
    if str(e) != "":
        logger.error(f"{e.__class__.__module__}.{e.__class__.__name__}: {e}")
    logger.error(f"{e.__class__.__module__}.{e.__class__.__name__}")
    logger.error(traceback.format_exc())


BANNER = """
 _______                                 __       __  __                               
/       \                               /  \     /  |/  |                              
$$$$$$$  |  ______    ______    _______ $$  \   /$$ |$$/  _______    ______    ______  
$$ |__$$ | /      \  /      \  /       |$$$  \ /$$$ |/  |/       \  /      \  /      \ 
$$    $$< /$$$$$$  |/$$$$$$  |/$$$$$$$/ $$$$  /$$$$ |$$ |$$$$$$$  |/$$$$$$  |/$$$$$$  |
$$$$$$$  |$$    $$ |$$ |  $$ |$$      \ $$ $$ $$/$$ |$$ |$$ |  $$ |$$    $$ |$$ |  $$/ 
$$ |  $$ |$$$$$$$$/ $$ \__$$ | $$$$$$  |$$ |$$$/ $$ |$$ |$$ |  $$ |$$$$$$$$/ $$ |      
$$ |  $$ |$$       |$$    $$ |/     $$/ $$ | $/  $$ |$$ |$$ |  $$ |$$       |$$ |      
$$/   $$/  $$$$$$$/  $$$$$$$ |$$$$$$$/  $$/      $$/ $$/ $$/   $$/  $$$$$$$/ $$/       
                          $$ |                                                         
                          $$ |                                                         
                          $$/                                                          
"""
