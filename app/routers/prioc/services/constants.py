from distutils.command.config import config

from app.common.config.config import config
from app.common.storage.implementations.disposable_gdf import DisposableTerritoryGDF
from app.common.storage.implementations.disposable_json import DisposableJSON


bucket_name = config.get("FILESERVER_BUCKET_NAME")
lo_hexes_filename= config.get("FILESERVER_LO_NAME")
indicators_weights_filename = config.get("INDICATORS_WEIGHTS_NAME")
object_indicators_min_val_filename = config.get("OBJECT_INDICATORS_MIN_VAL_NAME")
positive_service_cleaning_filename = config.get("POSITIVE_SERVICE_CLEANING_NAME")
negative_service_cleaning_filename = config.get("NEGATIVE_SERVICE_CLEANING_NAME")

LO_HEXES = DisposableTerritoryGDF()
LO_HEXES.try_init(bucket_name, lo_hexes_filename)
INDICATORS_WEIGHTS = DisposableJSON()
INDICATORS_WEIGHTS.try_init(bucket_name, indicators_weights_filename)
OBJECT_INDICATORS_MIN_VAL = DisposableJSON()
OBJECT_INDICATORS_MIN_VAL.try_init(bucket_name, object_indicators_min_val_filename)
POSITIVE_SERVICE_CLEANING = DisposableJSON()
POSITIVE_SERVICE_CLEANING.try_init(bucket_name, positive_service_cleaning_filename)
NEGATIVE_SERVICE_CLEANING = DisposableJSON()
NEGATIVE_SERVICE_CLEANING.try_init(bucket_name, negative_service_cleaning_filename)
