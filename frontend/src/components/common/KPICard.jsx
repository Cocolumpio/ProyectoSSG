export function KPICard({ icon: Icon, label, value, color, testId }) {
  const colorClasses = {
    brick: 'bg-[#994B49]/10 text-[#994B49]'
  };

  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm" data-testid={testId}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-gray-600 text-sm mb-1">{label}</p>
          <p className="text-3xl font-bold text-gray-900">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  );
}
