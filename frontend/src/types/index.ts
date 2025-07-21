export interface Story {
  id: string;
  title: string;
  content: string;
  author: string;
  createdAt: string;
  tags: string[];
  rating?: number;
  views: number;
}

export interface User {
  id: string;
  email: string;
  username: string;
  createdAt: string;
}

export interface SearchFilters {
  query?: string;
  author?: string;
  tags?: string[];
  dateRange?: {
    from: string;
    to: string;
  };
  sortBy?: 'createdAt' | 'rating' | 'views';
  sortOrder?: 'asc' | 'desc';
}

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}