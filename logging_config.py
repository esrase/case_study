import logging
import os

def setup_logger():
    logger = logging.getLogger("scraper_logger")
    logger.setLevel(logging.INFO)

    # Eğer logger'a daha önce handler eklenmişse tekrar eklememek için
    if not logger.handlers:
        # Log formatı
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

        # Log dosyası yolu (host'taki dizinde olacak)
        log_file = os.path.join(os.getcwd(), "scraper.log")

        # Dosya handler (logları dosyaya yazar)
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)

        # Terminal çıktısı için stream handler
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        # Handler'ları logger'a ekleme
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger






