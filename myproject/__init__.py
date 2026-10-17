import pymysql
pymysql.install_as_MySQLdb()

# 1. Bỏ qua kiểm tra phiên bản MariaDB cũ
from django.db.backends.base.base import BaseDatabaseWrapper
BaseDatabaseWrapper.check_database_version_supported = lambda self: None

# 2. Tắt tính năng RETURNING vì MariaDB 10.4 chưa hỗ trợ
from django.db.backends.mysql.features import DatabaseFeatures
DatabaseFeatures.can_return_columns_from_insert = False