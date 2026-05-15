Component({
  properties: {
    count: { type: Number, value: 0 },
    total: { type: Number, value: 0 }
  },

  methods: {
    onTap() {
      this.triggerEvent('tap');
    }
  }
});
