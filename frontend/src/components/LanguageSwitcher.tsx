import { GlobalOutlined } from '@ant-design/icons';
import { Dropdown } from 'antd';
import { useTranslation } from 'react-i18next';
import { LANGUAGES } from '../i18n';

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();

  const items = LANGUAGES.map((lang) => ({
    key: lang.code,
    label: lang.label,
  }));

  const handleChange = ({ key }: { key: string }) => {
    i18n.changeLanguage(key);
    localStorage.setItem('lang', key);
  };

  const current = LANGUAGES.find((l) => l.code === i18n.language) ?? LANGUAGES[0];

  return (
    <Dropdown menu={{ items, onClick: handleChange, selectedKeys: [current.code] }} trigger={['click']}>
      <span style={{ cursor: 'pointer', userSelect: 'none' }}>
        <GlobalOutlined style={{ marginRight: 4 }} />
        {current.label}
      </span>
    </Dropdown>
  );
}
