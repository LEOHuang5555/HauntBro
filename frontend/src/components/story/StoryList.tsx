import { Story } from '@/types';
import { StoryCard } from './StoryCard';

interface StoryListProps {
  stories: Story[];
  onStoryClick?: (story: Story) => void;
  isLoading?: boolean;
  error?: string | null;
}

export function StoryList({ stories, onStoryClick, isLoading, error }: StoryListProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-gray-200 rounded-lg h-48 animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-2">⚠️ Error loading stories</div>
        <p className="text-gray-600">{error}</p>
      </div>
    );
  }

  if (stories.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-6xl mb-4">👻</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No stories found</h3>
        <p className="text-gray-600">Try adjusting your search or filters</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {stories.map(story => (
        <StoryCard
          key={story.id}
          story={story}
          onClick={() => onStoryClick?.(story)}
        />
      ))}
    </div>
  );
}