
__copyright__    = 'Copyright (C) 2020 Masato Miyata'
__version__      = '2.0.0'
__license__      = 'MIT License'
__author__       = 'Masato Miyata'
__author_email__ = 'builelib@gmail.com'
__url__          = 'https://github.com/MasatoMiyata/builelib'

# 後方互換インポート（from builelib import XXX 形式で引き続き使用可能）
from builelib.systems import airconditioning_webpro, airconditioning
from builelib.systems import ventilation, lighting, hotwatersupply
from builelib.systems import elevator, photovoltaic, other_energy, cogeneration
from builelib.climate import climate
from builelib.envelope import shading
from builelib.input import make_inputdata
