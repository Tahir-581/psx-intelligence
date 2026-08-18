export type ProfileAlertTrigger = "13f" | "new_position" | "add_position" | "13d";

export type AlertRecord = {
  id: string;
  name: string;
  alertType: string;
  investor: string;
  minAmount?: number;
  email: string;
  active: boolean;
  description?: string;
  investorCik?: string;
  investorName?: string;
  trigger?: ProfileAlertTrigger;
};

export const STORAGE_KEY = "psx_sec_alerts";

export const DEFAULT_ALERTS: AlertRecord[] = [
  {
    id: "default-form4-buys",
    name: "Form 4 insider buys ≥ $1M",
    alertType: "form4_buy",
    investor: "any",
    minAmount: 1_000_000,
    email: "",
    active: true,
    description: "Alert when C-suite buys ≥ $1M of own stock",
  },
  {
    id: "default-13d-activist",
    name: "New 13D activist filing",
    alertType: "new_13d_13g",
    investor: "any",
    email: "",
    active: true,
    description: "Any 5%+ ownership stake filed",
  },
  {
    id: "default-berkshire-13f",
    name: "Berkshire Hathaway 13F filed",
    alertType: "new_13f",
    investor: "Berkshire Hathaway",
    investorCik: "1067983",
    investorName: "Berkshire Hathaway",
    email: "",
    active: true,
    description: "Quarterly 13F from Berkshire Hathaway",
  },
];

export const PROFILE_TRIGGER_LABELS: Record<ProfileAlertTrigger, string> = {
  "13f": "Any 13F filing",
  new_position: "New position opened",
  add_position: "Position increased",
  "13d": "13D activist filing",
};

export function loadAlerts(): AlertRecord[] {
  if (typeof window === "undefined") return DEFAULT_ALERTS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_ALERTS;
    const parsed = JSON.parse(raw) as AlertRecord[];
    return parsed.length ? parsed : DEFAULT_ALERTS;
  } catch {
    return DEFAULT_ALERTS;
  }
}

export function saveAlerts(alerts: AlertRecord[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(alerts));
}

export function appendAlert(alert: AlertRecord) {
  const alerts = loadAlerts();
  saveAlerts([...alerts.filter((a) => a.id !== alert.id), alert]);
}
