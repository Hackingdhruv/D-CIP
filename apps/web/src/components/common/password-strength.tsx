interface Props {
  password: string;
}

interface Strength {
  score: number; // 0-4
  label: string;
  color: string;
}

function getStrength(password: string): Strength {
  if (!password) return { score: 0, label: '', color: '' };
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  if (score <= 1) return { score: 1, label: 'Weak', color: 'bg-destructive' };
  if (score === 2) return { score: 2, label: 'Fair', color: 'bg-orange-400' };
  if (score === 3) return { score: 3, label: 'Good', color: 'bg-yellow-400' };
  return { score: 4, label: 'Strong', color: 'bg-green-500' };
}

export function PasswordStrength({ password }: Props) {
  if (!password) return null;
  const { score, label, color } = getStrength(password);

  return (
    <div className="mt-1.5 space-y-1">
      <div className="flex gap-1">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-colors duration-200 ${
              i <= score ? color : 'bg-muted'
            }`}
          />
        ))}
      </div>
      <p className={`text-xs ${score <= 1 ? 'text-destructive' : score <= 2 ? 'text-orange-500' : score === 3 ? 'text-yellow-600' : 'text-green-600'}`}>
        {label}
      </p>
    </div>
  );
}
