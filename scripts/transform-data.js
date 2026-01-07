#!/usr/bin/env node

/**
 * Transform Supabase data exports to API-compatible format
 *
 * Usage: node scripts/transform-data.js
 *
 * Transforms:
 *   data/books.json -> mock/data/books.json
 *   data/book_raitings.json -> mock/data/ratings.json
 *   Generates mock/data/users.json from unique user IDs
 *   Creates mock/db.json for JSON Server
 */

const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');
const MOCK_DIR = path.join(__dirname, '..', 'mock', 'data');
const CDN_BASE_URL = 'https://cdn.ilm-red.com';

// Ensure mock directory exists
if (!fs.existsSync(MOCK_DIR)) {
  fs.mkdirSync(MOCK_DIR, { recursive: true });
}

/**
 * Transform a Supabase book record to API Book format
 */
function transformBook(supabaseBook) {
  return {
    id: supabaseBook.id,
    title: supabaseBook.title,
    author: supabaseBook.author || null,
    description: supabaseBook.description || null,
    category: supabaseBook.category || 'other',
    language: supabaseBook.language || 'en',
    visibility: supabaseBook.visibility || (supabaseBook.is_public ? 'public' : 'private'),
    thumbnailUrl: supabaseBook.thumbnail_path
      ? `${CDN_BASE_URL}/thumbnails/${supabaseBook.thumbnail_path}`
      : null,
    stats: {
      viewCount: supabaseBook.view_count || 0,
      favoriteCount: Math.floor(Math.random() * 20), // Generate mock favorite count
      rating: (3 + Math.random() * 2).toFixed(1) // Generate 3.0-5.0 rating
    },
    status: 'active',
    createdAt: new Date(supabaseBook.uploaded_at).toISOString(),
    updatedAt: new Date(supabaseBook.updated_at).toISOString()
  };
}

/**
 * Transform a Supabase book record to API BookDetail format (extended)
 */
function transformBookDetail(supabaseBook) {
  const baseBook = transformBook(supabaseBook);
  return {
    ...baseBook,
    owner: {
      id: supabaseBook.user_id,
      username: `user_${supabaseBook.user_id.substring(0, 8)}`,
      displayName: `User ${supabaseBook.user_id.substring(0, 8)}`,
      avatarUrl: null
    },
    file: {
      path: supabaseBook.file_path,
      size: supabaseBook.file_size,
      mimeType: supabaseBook.mime_type,
      pageCount: Math.floor(50 + Math.random() * 300) // Mock page count
    },
    aiEnabled: supabaseBook.ai_processed || false,
    tags: Array.isArray(supabaseBook.tags) ? supabaseBook.tags : []
  };
}

/**
 * Transform a Supabase rating record to API Rating format
 */
function transformRating(supabaseRating, users) {
  const user = users.find(u => u.id === supabaseRating.user_id) || {
    id: supabaseRating.user_id,
    username: `user_${supabaseRating.user_id.substring(0, 8)}`,
    displayName: `User ${supabaseRating.user_id.substring(0, 8)}`,
    avatarUrl: null,
    bio: null
  };

  return {
    id: supabaseRating.id,
    bookId: supabaseRating.book_id,
    userId: supabaseRating.user_id,
    rating: supabaseRating.rating,
    review: supabaseRating.review || null,
    createdAt: new Date(supabaseRating.created_at).toISOString(),
    user: {
      id: user.id,
      username: user.username,
      displayName: user.displayName,
      avatarUrl: user.avatarUrl,
      bio: user.bio
    }
  };
}

/**
 * Generate mock user profiles from unique user IDs
 */
function generateUsers(userIds) {
  const firstNames = ['Alex', 'Sam', 'Jordan', 'Taylor', 'Casey', 'Morgan', 'Riley', 'Quinn', 'Avery', 'Peyton'];
  const lastNames = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez'];

  return [...new Set(userIds)].map((userId, index) => ({
    id: userId,
    email: `user${index + 1}@example.com`,
    username: `user_${userId.substring(0, 8)}`,
    displayName: `${firstNames[index % firstNames.length]} ${lastNames[index % lastNames.length]}`,
    avatarUrl: null,
    bio: `Book enthusiast and reader #${index + 1}`,
    roles: ['user'],
    preferences: {
      theme: 'system',
      language: 'en',
      notifications: { email: true, push: true }
    },
    createdAt: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000).toISOString()
  }));
}

/**
 * Main transformation function
 */
function transformAll() {
  console.log('Starting data transformation...\n');

  // Load source data
  const booksPath = path.join(DATA_DIR, 'books.json');
  const ratingsPath = path.join(DATA_DIR, 'book_raitings.json');

  if (!fs.existsSync(booksPath)) {
    console.error('Error: books.json not found in data directory');
    process.exit(1);
  }

  const supabaseBooks = JSON.parse(fs.readFileSync(booksPath, 'utf8'));
  console.log(`Loaded ${supabaseBooks.length} books from Supabase export`);

  // Transform books
  const books = supabaseBooks.map(transformBook);
  const bookDetails = supabaseBooks.map(transformBookDetail);

  // Collect unique user IDs
  const userIds = supabaseBooks.map(b => b.user_id);

  // Transform ratings if file exists
  let ratings = [];
  if (fs.existsSync(ratingsPath)) {
    const supabaseRatings = JSON.parse(fs.readFileSync(ratingsPath, 'utf8'));
    console.log(`Loaded ${supabaseRatings.length} ratings from Supabase export`);

    // Add rating user IDs
    supabaseRatings.forEach(r => userIds.push(r.user_id));

    // Generate users first (needed for rating transformation)
    const users = generateUsers(userIds);
    ratings = supabaseRatings.map(r => transformRating(r, users));

    // Write users
    fs.writeFileSync(
      path.join(MOCK_DIR, 'users.json'),
      JSON.stringify(users, null, 2)
    );
    console.log(`Generated ${users.length} mock user profiles`);
  } else {
    // Generate users without ratings
    const users = generateUsers(userIds);
    fs.writeFileSync(
      path.join(MOCK_DIR, 'users.json'),
      JSON.stringify(users, null, 2)
    );
    console.log(`Generated ${users.length} mock user profiles`);
  }

  // Write transformed books
  fs.writeFileSync(
    path.join(MOCK_DIR, 'books.json'),
    JSON.stringify(books, null, 2)
  );
  console.log(`Wrote ${books.length} books to mock/data/books.json`);

  // Write book details (extended format)
  fs.writeFileSync(
    path.join(MOCK_DIR, 'book-details.json'),
    JSON.stringify(bookDetails, null, 2)
  );
  console.log(`Wrote ${bookDetails.length} book details to mock/data/book-details.json`);

  // Write ratings
  fs.writeFileSync(
    path.join(MOCK_DIR, 'ratings.json'),
    JSON.stringify(ratings, null, 2)
  );
  console.log(`Wrote ${ratings.length} ratings to mock/data/ratings.json`);

  // Create JSON Server database
  const db = {
    books: books,
    'book-details': bookDetails,
    ratings: ratings,
    users: JSON.parse(fs.readFileSync(path.join(MOCK_DIR, 'users.json'), 'utf8'))
  };

  fs.writeFileSync(
    path.join(__dirname, '..', 'mock', 'db.json'),
    JSON.stringify(db, null, 2)
  );
  console.log('\nCreated mock/db.json for JSON Server');

  console.log('\nTransformation complete!');
  console.log('\nNext steps:');
  console.log('  1. npm run mock          - Start Prism mock server');
  console.log('  2. npm run mock:json-server - Start JSON Server');
}

// Run transformation
transformAll();
