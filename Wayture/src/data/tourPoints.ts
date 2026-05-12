export type TourPointData = {
  id: number;
  location: [number, number];
  name: string;
  description: string;
  field: string;
  cost: string;
  images: string[];
  position: { top: string; left: string };
  color: string;
};

export const tourPoints: TourPointData[] = [
  {
    id: 1,
    location: [10, 18],
    name: '溪谷观景台',
    description: '俯瞰峡谷全景，沿着小径感受自然。',
    field: '山景区',
    cost: '0.5h',
    images: [
      'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=60',
      'https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=900&q=60'
    ],
    position: { top: '18%', left: '24%' },
    color: '#F59E0B'
  },
  {
    id: 2,
    location: [40, 54],
    name: '古镇集市',
    description: '传统手工艺与特色小吃聚集，适合慢游。',
    field: '市集区',
    cost: '0.75h',
    images: [
      'https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=900&q=60',
      'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=900&q=60'
    ],
    position: { top: '38%', left: '54%' },
    color: '#10B981'
  },
  {
    id: 3,
    location: [60, 68],
    name: '湖畔茶屋',
    description: '在湖边品茶，观看水上风景。',
    field: '湖区',
    cost: '0.67h',
    images: [
      'https://images.unsplash.com/photo-1508830524289-0adcbe822b40?auto=format&fit=crop&w=900&q=60',
      'https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=900&q=60'
    ],
    position: { top: '58%', left: '68%' },
    color: '#3B82F6'
  },
  {
    id: 4,
    location: [72, 38],
    name: '历史博物馆',
    description: '了解本地文化与游览历史故事。',
    field: '市集区',
    cost: '0.6h',
    images: [
      'https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=900&q=60',
      'https://images.unsplash.com/photo-1523475496153-3c0a60d8b3a1?auto=format&fit=crop&w=900&q=60'
    ],
    position: { top: '70%', left: '38%' },
    color: '#8B5CF6'
  },
  {
    id: 5,
    location: [85, 20],
    name: '星空露营区',
    description: '夜晚观星，体验露营氛围。',
    field: '山景区',
    cost: '1h',
    images: [
      'https://images.unsplash.com/photo-1516900557540-6c00b9c1a8e0?auto=format&fit=crop&w=900&q=60',
      'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=900&q=60'
    ],
    position: { top: '82%', left: '18%' },
    color: '#EF4444'
  }
];
