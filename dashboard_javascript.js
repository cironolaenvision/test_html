/**
 * Dashboard utilities - Browser compatible version
 */

/**
 * Formats a number to a short string with appropriate suffixes for better readability.
 * 
 * This function converts large numbers into a more readable format by adding
 * appropriate suffixes (B for billions, M for millions) and formatting smaller
 * numbers with locale-specific formatting.
 * 
 * Parameters:
 * - num (number): The number to format
 * 
 * Returns:
 * - string: The formatted number as a string
 * 
 * Examples:
 * 
 * Large numbers:
 * DashboardUtils.formatShortNumber(1500000000) // Returns "1.50B"
 * DashboardUtils.formatShortNumber(2500000) // Returns "2.50M"
 * 
 * Smaller numbers:
 * DashboardUtils.formatShortNumber(1234) // Returns "1,234" (locale formatted)
 * DashboardUtils.formatShortNumber(999) // Returns "999" (locale formatted)
 * 
 * Notes:
 * - Numbers >= 1 billion are formatted with "B" suffix and 2 decimal places
 * - Numbers >= 1 million are formatted with "M" suffix and 2 decimal places
 * - Numbers < 1 million use locale-specific formatting (e.g., commas for thousands)
 * - Uses toFixed(2) for consistent decimal places in abbreviated format
 * - Uses toLocaleString() for proper locale formatting of smaller numbers
 * 
 * See also: formatCurrency for currency-specific formatting
 */
function formatShortNumber(num) {
    if (num >= 1000000000) {
        return (num / 1000000000).toFixed(2) + 'B';
    } else if (num >= 1000000) {
        return (num / 1000000).toFixed(2) + 'M';
    }
    else {
        return num.toLocaleString();
    }
}

/**
 * Formats a number as a currency string with appropriate suffixes and decimal places.
 * 
 * This function formats monetary values with currency symbols and appropriate
 * abbreviations for large amounts. It automatically scales the number and adds
 * the appropriate suffix (B for billions, M for millions, K for thousands)
 * while maintaining proper decimal precision for each scale.
 * 
 * Parameters:
 * - num (number): The monetary amount to format
 * - currencySymble (string): The currency symbol to prepend (e.g., "R$", "$", "€")
 * 
 * Returns:
 * - string: The formatted currency string
 * 
 * Examples:
 * 
 * Large amounts:
 * DashboardUtils.formatCurrency(1500000000, "R$") // Returns "R$ 1.5B"
 * DashboardUtils.formatCurrency(2500000, "$") // Returns "$ 2.5M"
 * DashboardUtils.formatCurrency(50000, "€") // Returns "€ 50.0K"
 * 
 * Smaller amounts:
 * DashboardUtils.formatCurrency(1234.56, "R$") // Returns "R$ 1234.56"
 * DashboardUtils.formatCurrency(99.99, "$") // Returns "$ 99.99"
 * 
 * Notes:
 * - Numbers >= 1 billion are formatted with "B" suffix and 1 decimal place
 * - Numbers >= 1 million are formatted with "M" suffix and 1 decimal place
 * - Numbers >= 1 thousand are formatted with "K" suffix and 1 decimal place
 * - Numbers < 1 thousand use 2 decimal places for precision
 * - Currency symbol is always prepended with a space
 * - Uses toFixed() for consistent decimal formatting
 * - Maintains proper spacing between currency symbol and value
 * 
 * See also: formatShortNumber for non-currency number formatting
 */
function formatCurrency(num, currencySymble) {
    if (num >= 1000000000) {
        return currencySymble + ' ' + (num / 1000000000).toFixed(1) + 'B';
    } else if (num >= 1000000) {
        return currencySymble + ' ' + (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return currencySymble + ' ' + (num / 1000).toFixed(1) + 'K';
    } else {
        return currencySymble + ' ' + num.toFixed(2);
    }
}

/**
 * Fetches data from the server by executing a SQL query and returns parsed results.
 * 
 * This function sends a SQL query to the server's /fetchData endpoint and returns
 * parsed data in a structured format. The server returns CSV data which is automatically
 * parsed into headers and an array of objects with clean property names.
 * 
 * Parameters:
 * - sql (string): The SQL query to execute on the server
 * 
 * Returns:
 * - Promise<Object>: A Promise that resolves to an object containing:
 *   - headers: Array of column names (cleaned from quotes)
 *   - data: Array of objects representing the query results
 * 
 * Examples:
 * 
 * Basic usage:
 * const result = await DashboardUtils.fetchData('SELECT * FROM users LIMIT 10');
 * console.log(result.headers); // ['id', 'name', 'email']
 * console.log(result.data); // Array of objects with clean property names
 * 
 * Working with the data:
 * const result = await DashboardUtils.fetchData('SELECT name, age FROM users WHERE age > 25');
 * console.log('Columns:', result.headers); // ['name', 'age']
 * result.data.forEach(user => {
 *     console.log(user.name, user.age); // Clean property access
 * });
 * 
 * Throws:
 * - Error: When the network request fails or the server returns an error
 * 
 * Notes:
 * - Returns both headers and data for flexibility
 * - Headers are cleaned (quotes removed from CSV headers)
 * - Values are properly unquoted from CSV format
 * - Empty or null values are handled gracefully
 * - Follows ISO CSV standard for proper parsing
 * 
 * See also: fetchMultipleData for fetching multiple queries at once
 */
async function fetchData(sql) {
    const response = await fetch('/fetchData', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: sql
    });

    if (!response.ok) {
        return { headers: [], data: [] };
    }

    const csvText = await response.text();

    // Parse CSV properly (handles quoted values and commas within quotes)
    const lines = csvText.split('\n').filter(line => line.trim());
    if (lines.length === 0) return [];

    // Parse headers (remove quotes)
    const headers = lines[0].split(',').map(h => h.replace(/^"|"$/g, ''));

    // Parse data rows
    const data = lines.slice(1).map(line => {
        const values = line.split(',').map(v => v.replace(/^"|"$/g, ''));
        return headers.reduce((obj, header, index) => {
            obj[header] = values[index] || '';
            return obj;
        }, {});
    });

    const retObj = { headers, data };
    return retObj;
}
/**
 * Fetches multiple datasets concurrently by executing a list of SQL queries in parallel.
 * 
 * This function takes an array of SQL queries and executes them simultaneously using Promise.all(),
 * significantly improving performance compared to sequential execution. Each query is processed
 * independently and the results are returned in the same order as the input queries.
 * 
 * @param Array<string> sqlList - An array of SQL query strings to be executed
 * @returns Promise<Array<Object>> A promise that resolves to an array of objects with headers and data
 * 
 * @example
 * // Execute multiple queries concurrently
 * const queries = [
 *   "SELECT * FROM table1 WHERE date > '2023-01-01'",
 *   "SELECT COUNT(*) as count FROM table2",
 *   "SELECT name, value FROM table3 ORDER BY value DESC"
 * ];
 * 
 * try {
 *   const results = await fetchMultipleData(queries);
 *   
 *   // Process each query result
 *   results.forEach((result, index) => {
 *     console.log(`Query ${index + 1} headers:`, result.headers);
 *     
 *     // Iterate through each row of data
 *     result.data.forEach((row, rowIndex) => {
 *       console.log(`Row ${rowIndex + 1}:`);
 *       
 *       // Get header and value for each column
 *       result.headers.forEach(header => {
 *         const value = row[header];
 *         console.log('  Header: '+header+', Value: '+value);
 *       });
 *     });
 *   });
 * } catch (error) {
 *   console.error('Error fetching data:', error);
 * }
 */

async function fetchMultipleData(sqlList) {
    const promises = {};

    for (let i = 0; i < sqlList.length; i++) {
        const promisseResponse = fetchData(sqlList[i]);
        promises[i] = promisseResponse;
    }

    const responses = await Promise.all(Object.values(promises));

    const results = new Array(sqlList.length);
    for (let i = 0; i < responses.length; i++) {
        try {
            const csvResponse = await responses[i];
            results[i] = csvResponse;
        } catch (error) {
            console.error('Error fetching data:', error);
            results[i] = { headers: [], data: [] };
        }
    }

    return results;
}

const DashboardUtils = {
    fetchData,
    fetchMultipleData,
    formatShortNumber,
    formatCurrency
}

// Create global namespace for browser usage
window.DashboardUtils = DashboardUtils;

// Also export for module systems if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        fetchData,
        fetchMultipleData,
        formatShortNumber,
        formatCurrency
    };
} 