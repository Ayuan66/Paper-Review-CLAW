import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  content: string;
}

export default function MarkdownViewer({ content }: Props) {
  const { t } = useTranslation();
  if (!content) {
    return <div style={{ color: '#999', padding: 16 }}>{t('results.noContent')}</div>;
  }
  return (
    <div style={{ padding: '8px 16px', lineHeight: 1.8 }}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
