/**
 * Job Hunter Platform — Generic Helpers
 */

export function debounce(func, wait = 300) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

export function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
