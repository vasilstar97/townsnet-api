import os

if 'URBAN_API' in os.environ:
    URBAN_API = os.environ['URBAN_API']
else:
    raise Exception('URBAN_API not found in env variables')

if 'TRANSPORT_FRAMES_API' in os.environ:
    TRANSPORT_FRAMES_API = os.environ['TRANSPORT_FRAMES_API']
else:
    raise Exception('TRANSPORT_FRAMES_API not found in env variables')

if 'DATA_PATH' in os.environ:
    DATA_PATH = os.path.abspath(os.environ['DATA_PATH'])
else:
    raise Exception('DATA_PATH not found in env variables')

EVALUATION_RESPONSE_MESSAGE = 'Evaluation started'
DEFAULT_CRS = 4326
