import { InboxOutlined } from '@ant-design/icons';
import { App, Typography, Upload } from 'antd';
import type { UploadProps } from 'antd';
import { useTranslation } from 'react-i18next';
import { uploadPdf } from '../api/client';
import { useReviewStore } from '../store/reviewStore';

const { Dragger } = Upload;
const { Text } = Typography;

export default function PdfUpload() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  const { setSessionId, setStatus, status } = useReviewStore();

  const props: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.pdf',
    showUploadList: false,
    disabled: status !== 'idle',
    customRequest: async ({ file, onSuccess, onError }) => {
      setStatus('uploading');
      try {
        const { session_id, filename } = await uploadPdf(file as File);
        setSessionId(session_id);
        setStatus('idle');
        message.success(t('upload.successMsg', { filename }));
        onSuccess?.({});
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : t('upload.uploadFailed');
        setStatus('error');
        message.error(msg);
        onError?.(new Error(msg));
      }
    },
    beforeUpload: (file) => {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        message.error(t('upload.onlyPdf'));
        return Upload.LIST_IGNORE;
      }
      if (file.size > 50 * 1024 * 1024) {
        message.error(t('upload.tooLarge'));
        return Upload.LIST_IGNORE;
      }
      return true;
    },
  };

  return (
    <Dragger {...props} style={{ padding: '8px' }}>
      <p className="ant-upload-drag-icon">
        <InboxOutlined />
      </p>
      <p className="ant-upload-text">{t('upload.dragText')}</p>
      <Text type="secondary" style={{ fontSize: 12 }}>
        {t('upload.supportText')}
      </Text>
    </Dragger>
  );
}
