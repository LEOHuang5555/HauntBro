import { Story } from '@/types';

interface StoryCardProps {
  story: Story;
  onClick?: () => void;
}

export function StoryCard({ story, onClick }: StoryCardProps) {
  return (
    <div 
      className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-lg font-semibold text-gray-900 hover:text-blue-600">
          {story.title}
        </h3>
        {story.rating && (
          <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded">
            ⭐ {story.rating}
          </span>
        )}
      </div>
      
      <p className="text-gray-600 text-sm mb-3 line-clamp-3">
        {story.content.substring(0, 200)}...
      </p>
      
      <div className="flex items-center justify-between text-sm text-gray-500">
        <div className="flex items-center space-x-4">
          <span>By {story.author}</span>
          <span>{story.views} views</span>
        </div>
        <span>{new Date(story.createdAt).toLocaleDateString()}</span>
      </div>
      
      {story.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {story.tags.slice(0, 3).map(tag => (
            <span 
              key={tag}
              className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded"
            >
              {tag}
            </span>
          ))}
          {story.tags.length > 3 && (
            <span className="text-gray-500 text-xs">
              +{story.tags.length - 3} more
            </span>
          )}
        </div>
      )}
    </div>
  );
}