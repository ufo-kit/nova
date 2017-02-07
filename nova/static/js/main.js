function readCookie(a) {
    var b = document.cookie.match('(^|;)\\s*' + a + '\\s*=\\s*([^;]+)');
    return b ? b.pop() : '';
}

var app = new Vue({
  el: '#body',
  data: {
    token: readCookie('token'),
    query: '',
    message: '',
    search_items: [],
    bookmarked_datasets: [],
    dataset_bookmarked: false,
    dataset_avg_rating: 0,
    dataset_base_rating: 0,
    dataset_half_star: false,
    dataset_reviews: [],
    dataset_review_count:0
  },
  watch: {
    query: function (data) {
      this.searchQuery (data)
    }
  },
  created: function() {
    var user_id = this.token.split('.')[0];
    var api_str = '/api/user/' + user_id + '/bookmarks/' + dataset_id;
    var headers = {
      'Auth-Token': this.token,
    }

    this.$http.get(api_str, {headers: headers}).then((response) => {
      if (response.body.exists) this.dataset_bookmarked = true;
    });

    api_str = '/api/datasets/' + dataset_id + '/reviews';

    this.$http.get(api_str, {headers: headers}).then((response) => {
      this.dataset_review_count = response.body.count;
      this.dataset_avg_rating = response.body.avg_rating;
      this.dataset_base_rating = Math.floor(this.dataset_avg_rating);
      this.dataset_half_star = (this.dataset_avg_rating - this.dataset_base_rating) >= .5;

      if (response.body.count > 0)
        this.dataset_reviews = response.body.data;
    });

    api_str = '/api/user/'+username+'/bookmarks'
      this.$http.get(api_str, {params: params}).then((response) => {
        this.bookmarked_datasets = response.body
    });
  },
  methods: {
    searchQuery: _.debounce(
      function (query) {
        var params = {
          q: query,
        }

        var headers = {
            'Auth-Token': this.token,
        }

        this.$http.get('/api/search', {params: params, headers: headers}).then((response) => {
          return response.json();
        }).then((items) => {
          this.search_items = items
        });
      },
      250
    ),
    bookmark: function (event) {
      var headers = {
        'Auth-Token': this.token,
      }

      var user_id = this.token.split('.')[0];
      var api_str = '/api/user/' + user_id + '/bookmarks/' + dataset_id;

      if (this.dataset_bookmarked) {
        this.$http.delete(api_str, {headers: headers}).then((response) => {
          this.dataset_bookmarked = response.status != 200;
        });
      }
      else {
        this.$http.post(api_str, null, {headers: headers}).then((response) => {
          this.dataset_bookmarked = response.status == 200;
        });
      }
    },
    timeSince: function(date) {
      date = new Date(date);
      current = new Date();
      delta = current.getTimezoneOffset();
      seconds = Math.floor((new Date() - date) / 1000) + delta*60;
      interval = Math.floor(seconds / 86400);
      if (interval >= 1) {
        return date.toLocaleString();
      }
      interval = Math.floor(seconds / 3600);
      if (interval >= 1) {
        return interval + " h ago";
      }
      interval = Math.floor(seconds / 60);
      if (interval >= 1) {
        return interval + " m ago";
      }
      return Math.floor(seconds) + " s ago";
    }
  }
})
