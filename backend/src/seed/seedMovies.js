const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const { Movie } = require('../models');
const sequelize = require('../config/db');

const moviesCsvPath = path.join(__dirname, '../../../dataset/movies_metadata.csv');
const creditsJsonPath = path.join(__dirname, 'credits_clean.json');

// Helper to parse the Python-dictionary-like strings in the CSV
const safeEval = (str) => {
    try {
        return new Function('return ' + str)();
    } catch (e) {
        return [];
    }
};

const loadCredits = () => {
    return new Promise((resolve, reject) => {
        try {
            console.log('Reading Credits JSON...');
            const data = fs.readFileSync(creditsJsonPath, 'utf8');
            const creditsMap = new Map();
            const json = JSON.parse(data);
            
            for (const [id, credit] of Object.entries(json)) {
                creditsMap.set(parseInt(id), credit);
            }
            
            console.log(`Loaded credits for ${creditsMap.size} movies.`);
            resolve(creditsMap);
        } catch (err) {
            reject(err);
        }
    });
};

const importMovies = async () => {
  try {
    await sequelize.authenticate();
    console.log('Database connected.');
    
    // Sync models (force: true to recreate tables and add new columns)
    // WARNING: This deletes all existing data!
    await sequelize.sync({ force: true });

    const creditsMap = await loadCredits();

    const movies = [];
    
    console.log('Reading Movies CSV...');
    
    fs.createReadStream(moviesCsvPath)
      .pipe(csv())
      .on('data', (row) => {
        if (!row.title) return;
        
        const releaseDate = row.release_date;
        const year = releaseDate ? new Date(releaseDate).getFullYear() : null;
        if (isNaN(year)) return;

        let genres = '';
        try {
            const genreList = safeEval(row.genres);
            if (Array.isArray(genreList)) {
                genres = genreList.map(g => g.name).join(', ');
            }
        } catch (e) {}

        const posterUrl = row.poster_path ? `https://image.tmdb.org/t/p/w500${row.poster_path}` : null;
        const imdbUrl = row.imdb_id ? `https://www.imdb.com/title/${row.imdb_id}/` : null;
        const tmdbId = parseInt(row.id);

        // Get credits from map
        const credits = creditsMap.get(tmdbId) || { actors: '', director: '' };

        movies.push({
            tmdbId: tmdbId || null,
            title: row.title,
            year: year || 0,
            genres: genres,
            description: row.overview,
            posterUrl: posterUrl,
            imdbUrl: imdbUrl,
            actors: credits.actors,
            director: credits.director
        });
      })
      .on('end', async () => {
        console.log(`Parsed ${movies.length} movies. Inserting into database...`);
        
        const chunkSize = 500;
        let insertedCount = 0;

        for (let i = 0; i < movies.length; i += chunkSize) {
            const chunk = movies.slice(i, i + chunkSize);
            try {
                await Movie.bulkCreate(chunk);
                insertedCount += chunk.length;
                if (insertedCount % 5000 === 0) {
                    console.log(`Inserted ${insertedCount} movies...`);
                }
            } catch (err) {
                console.error(`Error inserting batch starting at index ${i}:`, err.message);
            }
        }
        
        console.log('Movies imported successfully.');
        process.exit();
      });

  } catch (error) {
    console.error('Error importing movies:', error);
    process.exit(1);
  }
};

importMovies();

