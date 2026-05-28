// Test script
(async () => {
  console.log('TEST_START');
  try {
    const cats = await fetch('/api/staff/categories').then(r => r.json());
    console.log('CATS_RESULT:', JSON.stringify(cats));
  } catch(e) {
    console.log('CATS_ERR:', e.message);
  }
  try {
    const prods = await fetch('/api/staff/products?page=1&page_size=3').then(r => r.json());
    console.log('PRODS_RESULT:', prods.total);
  } catch(e) {
    console.log('PRODS_ERR:', e.message);
  }
  console.log('TEST_END');
})().catch(e => console.log('GLOBAL_ERR:', e.message));