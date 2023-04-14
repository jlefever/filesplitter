from filesplitter.loading import Dataset, load_dataset

ANDROID_BASE_DB = "../data/android-base.db"
ANDROID_SETTINGS_DB = "../data/android-settings.db"
BEAM_DB = "../data/beam.db"
DELTASPIKE_DB = "../data/deltaspike.db"
DUBBO_DB = "../data/dubbo.db"
FLUME_DB = "../data/flume.db"
GOBBLIN_DB = "../data/gobblin.db"
HBASE_DB = "../data/hbase.db"
HUDI_DB = "../data/hudi.db"
KAFKA_DB = "../data/kafka.db"
KNOX_DB = "../data/knox.db"
NIFI_DB = "../data/nifi.db"
OOZIE_DB = "../data/oozie.db"

ANDROID_BASE_VIEW = (ANDROID_BASE_DB, "core/java/android/view/View.java")
ANDROID_BASE_PACKAGE_MANAGER = (ANDROID_BASE_DB, "core/java/android/content/pm/PackageManager.java")
ANDROID_BASE_ACTIVITY = (ANDROID_BASE_DB, "core/java/android/app/Activity.java")
ANDROID_BASE_TEXT_VIEW = (ANDROID_BASE_DB, "core/java/android/widget/TextView.java")
ANDROID_BASE_SETTINGS = (ANDROID_BASE_DB, "core/java/android/provider/Settings.java")


ANDROID_SETTINGS_UTILS = (ANDROID_SETTINGS_DB, "src/com/android/settings/Utils.java")
ANDROID_SETTINGS_NETWORK_PROVIDER_SETTINGS = (
    ANDROID_SETTINGS_DB,
    "src/com/android/settings/network/NetworkProviderSettings.java",
)

HUDI_HOODIE_WRITE_CONFIG = (
    HUDI_DB,
    "hudi-client/hudi-client-common/src/main/java/org/apache/hudi/config/HoodieWriteConfig.java",
)


def load_subject(subject: tuple[str, str]) -> Dataset:
    return load_dataset(*subject)
