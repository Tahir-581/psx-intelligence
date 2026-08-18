import { SmartMoneyLayoutClient } from "./layout-client";

export default function SmartMoneyLayout({ children }: { children: React.ReactNode }) {
  return <SmartMoneyLayoutClient>{children}</SmartMoneyLayoutClient>;
}
