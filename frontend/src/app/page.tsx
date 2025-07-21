'use client';

import { useState } from 'react';
import { SearchBar } from '@/components/search/SearchBar';
import { SearchFilters } from '@/components/search/SearchFilters';
import { StoryList } from '@/components/story/StoryList';
import { StoryDetail } from '@/components/story/StoryDetail';
import { Story, SearchFilters as SearchFiltersType } from '@/types';

export default function Home() {
  const [stories, setStories] = useState<Story[]>([]);
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async () => {
    setIsLoading(true);
    setError(null);
    setHasSearched(true);
    
    try {
      const mockStories: Story[] = [
        {
          id: '1',
          title: 'The Haunted Mansion on Elm Street',
          content: 'It was a dark and stormy night when I first saw the mansion...',
          author: 'GhostHunter99',
          createdAt: '2024-01-15T00:00:00Z',
          tags: ['mansion', 'haunted', 'supernatural'],
          rating: 4.5,
          views: 1234
        },
        {
          id: '2',
          title: 'Strange Sounds in the Attic',
          content: 'Every night at 3 AM, I hear footsteps above my bedroom...',
          author: 'ScareDCat',
          createdAt: '2024-01-10T00:00:00Z',
          tags: ['attic', 'sounds', 'mystery'],
          rating: 4.2,
          views: 856
        }
      ];
      
      setTimeout(() => {
        setStories(mockStories);
        setIsLoading(false);
      }, 1000);
    } catch {
      setError('Failed to search stories');
      setIsLoading(false);
    }
  };

  const handleFiltersChange = (filters: SearchFiltersType) => {
    console.log('Filters changed:', filters);
  };

  const handleStoryClick = (story: Story) => {
    setSelectedStory(story);
  };

  const handleBackToResults = () => {
    setSelectedStory(null);
  };

  if (selectedStory) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4">
        <StoryDetail story={selectedStory} onBack={handleBackToResults} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900 text-center mb-8">
            👻 HauntBro
          </h1>
          <p className="text-gray-600 text-center mb-8">
            Discover spine-chilling ghost stories from around the internet
          </p>
          <SearchBar onSearch={handleSearch} isLoading={isLoading} />
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {hasSearched && (
          <>
            <SearchFilters onFiltersChange={handleFiltersChange} />
            <StoryList
              stories={stories}
              onStoryClick={handleStoryClick}
              isLoading={isLoading}
              error={error}
            />
          </>
        )}
        
        {!hasSearched && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">🔍</div>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              Start Your Ghost Story Journey
            </h2>
            <p className="text-gray-600 max-w-md mx-auto">
              Search through thousands of spine-tingling tales from PTT Marvel and Reddit.
              Use the search bar above to begin exploring.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
