import { getAvatarColors } from "@/lib/smart-money-utils";

const SIZE_MAP = {
  sm: "size-6 text-[10px]",
  md: "size-7 text-[10px]",
  lg: "size-12 text-base",
} as const;

export function InvestorAvatar({
  initials,
  color,
  size = "md",
}: {
  initials: string;
  color: string;
  size?: keyof typeof SIZE_MAP;
}) {
  const { bg, text } = getAvatarColors(color);
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-full font-medium ${bg} ${text} ${SIZE_MAP[size]}`}
    >
      {initials}
    </span>
  );
}
