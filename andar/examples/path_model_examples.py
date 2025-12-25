from andar import FieldConf, PathModel, SafePatterns

# A date archived path model
date_archived_pm = PathModel(
    template="/{base_path}/{sub_folder}/{date}/{name}_{datetime}.{ext}",
    fields={
        "base_path": FieldConf(pattern=SafePatterns.DIRPATH),  #  safe pattern for directories
        "sub_folder": FieldConf(pattern=SafePatterns.NAME),  #  safe pattern for a folder
        "date": FieldConf(pattern=r"\d{4}-\d{2}-\d{2}", date_format="%Y-%m-%d"),  # date converter
        "name": FieldConf(pattern=SafePatterns.FIELD),  # safe pattern for a field (without separator characters)
        "datetime": FieldConf(pattern=r"\d{8}_\d{6}", datetime_format="%Y%m%d_%H%M%S"),  # datetime converter
        "ext": FieldConf(pattern=SafePatterns.EXTENSION),  #  safe pattern for an extension
    },
)

# A data mesh path model

data_mesh_pm = PathModel(
    template="/{domain}/{layer}/{product}/{aggregation}/{product}_{date}.{ext}",
    fields={
        "domain": FieldConf(pattern=SafePatterns.NAME),  # sales, marketing, HR, finance, etc
        "layer": FieldConf(pattern=SafePatterns.NAME),  # raw, intermediate, mart, etc
        "product": FieldConf(pattern=SafePatterns.NAME),
        "aggregation": FieldConf(pattern=SafePatterns.NAME),  # daily, weekly, monthly, etc
        "date": FieldConf(pattern=r"\d{8}", datetime_format="%Y%m%d"),
        "ext": FieldConf(pattern=SafePatterns.EXTENSION),
    },
)
