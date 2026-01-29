import React from 'react';

interface StatCardProps {
  title: string;
  value: number | string;
  icon?: React.ReactNode;
  bgColor?: string;
  textColor?: string;
  onClick?: () => void;
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  bgColor = 'bg-blue-50',
  textColor = 'text-blue-900',
  onClick
}) => {
  return (
    <div
      onClick={onClick}
      className={`${bgColor} rounded-lg p-6 shadow-sm ${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''}`}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className={`text-3xl font-bold ${textColor} mt-2`}>{value}</p>
        </div>
        {icon && (
          <div className={`${textColor} opacity-50`}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
};

export default StatCard;
