/**
 * GitHub-style pixel identicon avatar (5×5 block grid).
 */
type GitHubPixelAvatarProps = {
  size?: number;
  className?: string;
};

/** Fixed pleasant pattern reminiscent of GitHub identicons */
const PIXELS: boolean[][] = [
  [true, false, true, false, true],
  [false, true, true, true, false],
  [true, true, false, true, true],
  [false, true, true, true, false],
  [true, false, true, false, true],
];

const FILL = "#24292f";
const ACCENT = "#2da44e";

export function GitHubPixelAvatar({
  size = 32,
  className = "",
}: GitHubPixelAvatarProps) {
  const cell = size / 5;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label="GitHub pixel avatar"
      className={`block shrink-0 ${className}`}
      style={{ imageRendering: "pixelated" }}
    >
      <rect width={size} height={size} fill="#f6f8fa" />
      {PIXELS.map((row, y) =>
        row.map((on, x) =>
          on ? (
            <rect
              key={`${x}-${y}`}
              x={x * cell}
              y={y * cell}
              width={cell}
              height={cell}
              fill={(x + y) % 2 === 0 ? FILL : ACCENT}
            />
          ) : null,
        ),
      )}
    </svg>
  );
}
