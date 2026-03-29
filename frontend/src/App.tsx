import { App as AntApp, ConfigProvider, theme as antTheme } from "antd";
import enUS from "antd/locale/en_US";
import jaJP from "antd/locale/ja_JP";
import zhCN from "antd/locale/zh_CN";
import { useTranslation } from "react-i18next";
import ReviewPage from "./pages/ReviewPage";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ANT_LOCALES: Record<string, any> = {
  zh: zhCN,
  en: enUS,
  ja: jaJP,
};

export default function App() {
  const { i18n } = useTranslation();
  const antLocale = ANT_LOCALES[i18n.language] ?? zhCN;

  return (
    <ConfigProvider
      locale={antLocale}
      theme={{
        token: {
          colorPrimary: "#2563eb",
          borderRadius: 8,
          borderRadiusLG: 12,
        },
        algorithm: antTheme.defaultAlgorithm,
      }}
    >
      <AntApp>
        <ReviewPage />
      </AntApp>
    </ConfigProvider>
  );
}
