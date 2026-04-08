from model import Battlefield
from model.General import General
from Constant import LOGS_FOLDER
import os


class Logger():
    """
    Handles logging operations for the simulation, recording general 
    information and specific army statistics into external files.

    Attributes:
        logfil (str): The full system path to the active log file.
    """

    def __init__(self, logfile:str):
        """
        Initializes the Logger by ensuring the log directory exists 
        and setting the target file path.
        """
        if not os.path.exists(LOGS_FOLDER):
            os.makedirs(LOGS_FOLDER)

        self.logfil = LOGS_FOLDER + logfile

    def log(self, info:str):
        """
        Appends a raw string of information to the end of the log file.
        """
        stream = open(self.logfil, "a")
        if stream:
            stream.write(info)
        stream.close()

    def log_info_from_general(self, general:General, battlefield:Battlefield):
        """
        Records a detailed snapshot of a general's current state, including 
        their strategy and the count of remaining units categorized by type.
        """
        stream = open(self.logfil, "a")
        if stream:
            stream.write(f"General: {general.name} : {general.strategy} \n")
            stats = general.get_stats_by_unit_type(battlefield)
            for unit_type, count in stats.items():
                stream.write(f" - {unit_type}: {count} units\n")
            stream.write("\n")

        stream.close()
