export function KPICard({ icon: Icon, label, value, color, testId, tooltip }) {
  const colorClasses = {
    brick: 'bg-[#994B49]/10 text-[#994B49]'
  };

  return (
    <div
      className="bg-[#15151B] rounded-xl p-6 border border-white/10 shadow-sm relative group"
      data-testid={testId}
      title={tooltip || undefined}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-white/60 text-sm mb-1">{label}</p>
          <p className="text-3xl font-bold text-white">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  );
}
