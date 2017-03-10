Vue.component('searchresults', {
  template: '#search-results-template',
  props: ['show', 'search_query'],
  methods: {
    showFullResults: function() {
      this.$parent.$options.methods.showFullResults()
    }
  }
})

var mainsearch = new Vue ({
  el:'#main-search',
  data: {
    token: readCookie('token'),
    search_query: '',
    search_results: [],
    show_results: false
  },
  watch: {
    search_query: function (data) {
      if (data == '')
        this.hideResults()
      else 
        this.searchQuery(data)
    }
  },
  methods: {
    searchQuery: _.debounce(
      function (query) {
        var params = {
          q: query
        }
        var headers = {
            'Auth-Token': this.token
        }
        this.$http.get('/api/search', {params: params, headers: headers}).then((response) => {
          return response.json();
        }).then((items) => {
          this.search_results = items
          if (items.length >0) this.showResults()
          else this.hideResults()
        })
      },
      250
    ),
    showResults: function() {
      this.show_results = true
    },
    hideResults: function() {
      this.show_results = false
    },
    showFullResults: function(query) {
      window.location = "/search?q="+this.search_query
    },
    clearQuery: function () {
      this.search_query = ''
    },
  },
})
