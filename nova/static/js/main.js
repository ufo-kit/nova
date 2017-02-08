function readCookie(a) {
    var b = document.cookie.match('(^|;)\\s*' + a + '\\s*=\\s*([^;]+)');
    return b ? b.pop() : '';
}

Vue.component('confirmdeletion', {
  template: '#modal-template',
  props: ['show']
})


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
    dataset_review_count: 0,
    show_review_input: true,
    isRated: false,
    rating_notified: false,
    review_text: '',
    n: 0,
    review_being_updated: false,
    review_under_updation: '',
    show_modal_delete_review: false,
   },
  watch: {
    query: function (data) {
      this.searchQuery (data)
    }
  },
  created: function() {
    var user_id = this.token.split('.')[0]
    var api_str = '/api/user/' + user_id + '/bookmarks/' + dataset_id
    var headers = {
      'Auth-Token': this.token
    }

    this.$http.get(api_str, {headers: headers}).then((response) => {
      if (response.body.exists) this.dataset_bookmarked = true
    })
    this.loadReviews(headers)
    api_str = '/api/user/'+username+'/bookmarks'
      this.$http.get(api_str, {headers: headers}).then((response) => {
        this.bookmarked_datasets = response.body
    })
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
          this.search_items = items
        })
      },
      250
    ),
    bookmark: function (event) {
      var headers = {
        'Auth-Token': this.token
      }

      var user_id = this.token.split('.')[0]
      var api_str = '/api/user/' + user_id + '/bookmarks/' + dataset_id

      if (this.dataset_bookmarked) {
        this.$http.delete(api_str, {headers: headers}).then((response) => {
          this.dataset_bookmarked = response.status != 200
        })
      }
      else {
        this.$http.post(api_str, null, {headers: headers}).then((response) => {
          this.dataset_bookmarked = response.status == 200
        })
      }
    },
    loadReviews: function (headers) {
      api_str = '/api/datasets/'+dataset_id+'/reviews'
      this.$http.get(api_str, {headers: headers}).then((response) => {
        this.dataset_review_count = parseInt(response.body.count)
        this.dataset_avg_rating = response.body.avg_rating
        this.dataset_base_rating = Math.floor(this.dataset_avg_rating)
        if (this.dataset_avg_rating - this.dataset_base_rating >= .5) this.dataset_half_star = true
        else this.dataset_half_star = false
        if (response.body.count > 0) { 
          this.dataset_reviews = response.body.data
          this.show_review_input = ! response.body.self_reviewed
        }
      })
    },
    rate: function(n) { 
      this.n = n
      this.isRated = true
      this.rating_notified = false
    },
    putReview: function(comment, rating) {
      var headers = {
        'Auth-Token': this.token
      }
      var jsonBody = {
        'comment':comment,
        'rating':rating
      }
      var user_id = this.token.split('.')[0]
      var api_str = '/api/datasets/'+dataset_id+'/reviews/'+user_id
      this.$http.put(api_str, jsonBody, {headers: headers}).then((response) => {
        this.loadReviews(headers)
      })
    },
    beginUpdatingReview: function(review) {
      this.n = review.rating
      this.review_text = review.comment
      this.review_under_updation = review.id
      this.review_being_updated = true
    },
    endUpdatingReview: function() {
      this.review_being_updated = false
    },
    sendUpdatedReview: function() {
      this.review_being_updated = false
      this.putReview(this.review_text, this.n)
    },
    sendNewReview: function() {
      if (this.isRated && this.n>0) this.putReview(this.review_text, this.n)
      else this.rating_notified = true
    },
    beginDeletingReview: function(review) {
      this.review_under_updation = review
      this.show_modal_delete_review = true
    },
    deleteReview: function() {
      this.review_text = ''
      this.n = 0
      this.isRated = false
      var headers = {
        'Auth-Token': this.token
      }
      var api_str = '/api/datasets/'+this.review_under_updation.dataset_id+'/reviews/'+this.review_under_updation.user_id
      this.$http.delete(api_str, {headers: headers}).then((response) => {
        if (response.status == 200)
        this.show_modal_delete_review = false
      })
      this.loadReviews(headers)
    },
    timeSince: function(date) {
      date = new Date(date)
      current = new Date()
      delta = current.getTimezoneOffset()
      seconds = Math.floor((new Date() - date) / 1000) + delta*60
      interval = Math.floor(seconds / 86400)
      if (interval >= 1) {
        return date.toLocaleString()
      }
      interval = Math.floor(seconds / 3600)
      if (interval >= 1) {
        return interval + " h ago"
      }
      interval = Math.floor(seconds / 60)
      if (interval >= 1) {
        return interval + " m ago"
      }
      return Math.floor(seconds) + " s ago"
    }, 
    dismissModal: function ()
    {
      this.show_modal_delete_review = false
    }
  }
})
