from andar import FieldConf, PathModel, SafePatterns

# A date archived path model

date_archived_pm = PathModel(
    template="/{base_path}/{subfolder}/{date_path}/{date_prefix}_{name}_{datetime_suffix}.{ext}",
    fields={
        #  safe pattern for directories
        "base_path": FieldConf(pattern=SafePatterns.DIRPATH),
        #  safe pattern for a folder
        "subfolder": FieldConf(pattern=SafePatterns.NAME),
        # date converter
        "date_path": FieldConf(pattern=r"\d{4}/\d{2}/\d{2}", date_format="%Y/%m/%d"),
        # date converter
        "date_prefix": FieldConf(pattern=r"\d{4}-\d{2}-\d{2}", date_format="%Y-%m-%d"),
        # safe pattern for a field (without separator characters)
        "name": FieldConf(pattern=SafePatterns.FIELD),
        # datetime converter
        "datetime_suffix": FieldConf(pattern=r"\d{8}_\d{6}", datetime_format="%Y%m%d_%H%M%S"),
        #  safe pattern for an extension
        "ext": FieldConf(pattern=SafePatterns.EXTENSION),
    },
)

# A data mesh path model

data_mesh_pm = PathModel(
    template="/{domain}/{layer}/{product}/{aggregation}/{date}_{product}.{ext}",
    fields={
        "domain": FieldConf(pattern=SafePatterns.NAME),  # sales, marketing, HR, finance, etc
        "layer": FieldConf(pattern=SafePatterns.NAME),  # raw, intermediate, mart, etc
        "product": FieldConf(pattern=SafePatterns.NAME),  # orders, revenues, taxes, campaigns, etc
        "aggregation": FieldConf(pattern=SafePatterns.NAME),  # daily, weekly, monthly, etc
        "date": FieldConf(pattern=r"\d{8}", datetime_format="%Y%m%d"),  # product date
        "ext": FieldConf(pattern=SafePatterns.EXTENSION),  # csv, xls, parquet, etc
    },
)
