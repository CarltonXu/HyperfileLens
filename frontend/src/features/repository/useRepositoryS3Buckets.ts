import { ref, watch, type Ref } from "vue";
import { repositoriesApi } from "@/api";

type Translate = (key: string, params?: Record<string, any>) => string;

type RepositoryDraft = {
  s3_config: {
    endpoint: string;
    bucket: string;
    region: string;
    access_key: string;
    secret_key: string;
    use_tls: boolean;
    bucket_mode: "existing" | "new";
  };
};

const BUCKET_NAME_RULES = {
  minLength: 3,
  maxLength: 63,
  ipPattern: /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/,
  consecutivePattern: /\.\.|\.-|-\./,
};

export function useRepositoryS3Buckets(options: {
  t: Translate;
  newRepo: Ref<RepositoryDraft>;
  clearError: (field: string) => void;
}) {
  const { t, newRepo, clearError } = options;

  const s3BucketList = ref<
    Array<{ name: string; creation_date?: string; size?: number }>
  >([]);
  const isLoadingBuckets = ref(false);
  const bucketListError = ref("");
  const checkingBucketName = ref(false);
  const bucketNameAvailable = ref<boolean | null>(null);
  const bucketNameMessage = ref("");

  function validateBucketName(name: string): { valid: boolean; message: string } {
    if (!name) {
      return { valid: false, message: t("repository.s3.bucketNameRequired") };
    }

    if (name.length < BUCKET_NAME_RULES.minLength) {
      return {
        valid: false,
        message: t("repository.s3.bucketNameTooShort", {
          min: BUCKET_NAME_RULES.minLength,
        }),
      };
    }

    if (name.length > BUCKET_NAME_RULES.maxLength) {
      return {
        valid: false,
        message: t("repository.s3.bucketNameTooLong", {
          max: BUCKET_NAME_RULES.maxLength,
        }),
      };
    }

    if (!/^[a-z0-9.-]+$/.test(name)) {
      return {
        valid: false,
        message: t("repository.s3.bucketNameInvalidChars"),
      };
    }

    if (!/^[a-z0-9]/.test(name) || !/[a-z0-9]$/.test(name)) {
      return { valid: false, message: t("repository.s3.bucketNameStartEnd") };
    }

    if (BUCKET_NAME_RULES.ipPattern.test(name)) {
      return { valid: false, message: t("repository.s3.bucketNameIPFormat") };
    }

    if (BUCKET_NAME_RULES.consecutivePattern.test(name)) {
      return { valid: false, message: t("repository.s3.bucketNameConsecutive") };
    }

    return { valid: true, message: "" };
  }

  async function fetchBucketList() {
    const { endpoint, access_key, secret_key, use_tls } =
      newRepo.value.s3_config;

    if (!endpoint || !access_key || !secret_key) {
      bucketListError.value = t("repository.s3.fillCredentialsFirst");
      return;
    }

    try {
      const url = new URL(endpoint);
      if (!url.hostname) {
        bucketListError.value = t("repository.s3.invalidEndpoint");
        return;
      }
    } catch {
      bucketListError.value = t("repository.s3.invalidEndpoint");
      return;
    }

    isLoadingBuckets.value = true;
    bucketListError.value = "";
    s3BucketList.value = [];

    try {
      const response = await repositoriesApi.listBuckets({
        endpoint,
        region: newRepo.value.s3_config.region || undefined,
        access_key,
        secret_key,
        use_tls,
        filter_by_region: true,
      });

      if (response.data.buckets) {
        s3BucketList.value = response.data.buckets;
      }

      if (response.data.suggestion && response.data.matched_count === 0) {
        bucketListError.value = response.data.suggestion;
      }
    } catch (error: any) {
      console.error("[S3] Failed to fetch bucket list:", error);

      if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
        bucketListError.value = t("repository.s3.connectionTimeout");
        return;
      }

      if (
        error.code === "ERR_NETWORK" ||
        error.message?.includes("Network Error")
      ) {
        bucketListError.value = t("repository.s3.networkError");
        return;
      }

      const errorData = error.response?.data || {};
      let errorMessage = t("repository.s3.fetchBucketsFailed");

      if (errorData.message) {
        errorMessage = errorData.message;
      }

      if (errorData.hint) {
        errorMessage += ` ${errorData.hint}`;
      }

      if (errorData.error_code) {
        console.error(
          `[S3] Error code: ${errorData.error_code}, HTTP: ${errorData.http_status}`,
        );
        errorMessage += ` (${errorData.error_code})`;
      }

      if (errorData.details) {
        console.error(`[S3] Details: ${errorData.details}`);
      }

      bucketListError.value = errorMessage;
    } finally {
      isLoadingBuckets.value = false;
    }
  }

  async function checkBucketNameAvailability() {
    const { endpoint, access_key, secret_key, bucket, use_tls } =
      newRepo.value.s3_config;

    const validation = validateBucketName(bucket);
    if (!validation.valid) {
      bucketNameAvailable.value = false;
      bucketNameMessage.value = validation.message;
      return;
    }

    if (!endpoint || !access_key || !secret_key) {
      bucketNameMessage.value = t("repository.s3.fillCredentialsFirst");
      return;
    }

    checkingBucketName.value = true;
    bucketNameMessage.value = "";

    try {
      const response = await repositoriesApi.checkBucketName({
        endpoint,
        region: newRepo.value.s3_config.region || undefined,
        access_key,
        secret_key,
        bucket_name: bucket,
        use_tls,
      });

      bucketNameAvailable.value = response.data.available;
      bucketNameMessage.value = response.data.message;
    } catch (error: any) {
      console.error("[S3] Failed to check bucket name:", error);

      const errorData = error.response?.data || {};
      let errorMessage = t("repository.s3.checkBucketFailed");

      if (errorData.message) {
        errorMessage = errorData.message;
      }

      if (errorData.hint) {
        errorMessage += ` ${errorData.hint}`;
      }

      if (errorData.error_code) {
        console.error(`[S3] Error code: ${errorData.error_code}`);
      }

      bucketNameAvailable.value = false;
      bucketNameMessage.value = errorMessage;
    } finally {
      checkingBucketName.value = false;
    }
  }

  function resetBucketState() {
    s3BucketList.value = [];
    bucketListError.value = "";
    bucketNameAvailable.value = null;
    bucketNameMessage.value = "";
  }

  watch(
    () => newRepo.value.s3_config.bucket_mode,
    () => {
      newRepo.value.s3_config.bucket = "";
      resetBucketState();
      clearError("bucket");
    },
  );

  watch(
    () => newRepo.value.s3_config.bucket,
    (newName) => {
      if (newRepo.value.s3_config.bucket_mode === "new") {
        bucketNameAvailable.value = null;
        bucketNameMessage.value = "";

        if (newName) {
          const validation = validateBucketName(newName);
          if (!validation.valid) {
            bucketNameMessage.value = validation.message;
          }
        }
      }
    },
  );

  watch(
    [
      () => newRepo.value.s3_config.endpoint,
      () => newRepo.value.s3_config.access_key,
      () => newRepo.value.s3_config.secret_key,
    ],
    resetBucketState,
  );

  return {
    s3BucketList,
    isLoadingBuckets,
    bucketListError,
    checkingBucketName,
    bucketNameAvailable,
    bucketNameMessage,
    validateBucketName,
    fetchBucketList,
    checkBucketNameAvailability,
    resetBucketState,
  };
}
