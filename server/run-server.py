import sys
# add
sys.path.extend( [ '..', 'web.zip'] )

import web
import boolean

urls = (
  '/(.*)', 'index'  
)

render = web.template.render('templates/', cache=False )

class index:
    def GET(self, name):
        print render.index( name )

web.webapi.internalerror = web.debugerror

if __name__ == "__main__": 
    web.run(urls, globals(), web.reloader)