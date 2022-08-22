import consts
from datetime import datetime

class Logger:

  @classmethod
  def info(self, message):
    date = self.get_date()
    console_log_line = f"{consts.INFO_COLOR}[INFO]{consts.NORMAL_COLOR} @ {date} - {message}"
    log_file_line = f"[INFO] @ {date} - {message}\n"
    print(console_log_line)
    with open(self.log_file_path, "a", encoding='utf-8') as log_file:
      log_file.write(log_file_line)

  @classmethod
  def warning(self, message):
    date = self.get_date()
    console_log_line = f"{consts.WARNING_COLOR}[WARNING]{consts.NORMAL_COLOR} @ {date} - {message}"
    log_file_line = f"[WARNING] @ {date} - {message}\n"
    print(console_log_line)
    with open(self.log_file_path, "a", encoding='utf-8') as log_file:
      log_file.write(log_file_line)
      
  @classmethod
  def error(self, message):
    date = self.get_date()
    console_log_line = f"{consts.ERROR_COLOR}[ERROR]{consts.NORMAL_COLOR} @ {date} - {message}"
    log_file_line = f"[ERROR] @ {date} - {message}\n"
    print(console_log_line)
    with open(self.log_file_path, "a", encoding='utf-8') as log_file:
      log_file.write(log_file_line)

  @staticmethod
  def get_date():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")