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
