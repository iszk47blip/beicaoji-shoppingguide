Component({
  properties: {
    product: { type: Object, value: {} },
    quantity: { type: Number, value: 0 }
  },

  data: {
    emoji: ''
  },

  observers: {
    'product.category': function(cat) {
      const map = { biscuit: '🍪', bread: '🍞', tea: '🍵', toy: '🎐' };
      this.setData({ emoji: map[cat] || '🌿' });
    }
  }
});
