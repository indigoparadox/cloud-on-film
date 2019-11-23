
module.exports = function( grunt ) {

   var env = grunt.option( 'env' ) || 'std';
   var static_dir = 'src/static/';

   if( 'docker' == env ) {
      static_dir = 'app/static/';
   }

   grunt.initConfig( {
      copy: {
         main: {
            files: [
               {expand: true, src: [
                  'node_modules/jquery/dist/jquery.min.js',
                  'node_modules/bootstrap/dist/js/bootstrap.min.js',
                  'node_modules/bootstrap/dist/css/bootstrap.min.css',
                  'node_modules/popper.js/dist/umd/popper.min.js',
                  'node_modules/unveil2/dist/jquery.unveil2.min.js',
                  'node_modules/featherlight/release/featherlight.min.css',
                  'node_modules/featherlight/release/featherlight.min.js',
                  'node_modules/featherlight/release/featherlight.gallery.min.css',
                  'node_modules/featherlight/release/featherlight.gallery.min.js'
               ],
               dest: static_dir, flatten: true},
            ]
         }
      }
   } )

   grunt.loadNpmTasks( 'grunt-contrib-copy' );

   grunt.registerTask( 'default', ['copy'] );
};

