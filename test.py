import httpx
import urllib.parse
async def VidPlayProxy(url:str=None):
    if url is None:
        return ('status_code=404')
    else:
        url = urllib.parse.unquote(url)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={'Referer': 'https://vidsrc.to'})
            content_type = response.headers.get("content-type")
            if content_type != "application/vnd.apple.mpegurl":
                return (response.content,content_type)
            m3u8_content = response.text
            proxy_url = "{PROXY}/vidplay?url="  # Change the PROXY to your deployment.
            m3u8_lines = m3u8_content.splitlines()
            for i, line in enumerate(m3u8_lines):
                if line.startswith("http"):
                    m3u8_lines[i] = proxy_url + urllib.parse.quote(line)
            modified_m3u8_content = "\n".join(m3u8_lines)
            return (modified_m3u8_content, content_type)
url = 'https://govbw.vid109d224.site/_v2-pvzv/12a3c523f9105800ed8c394685aeeb0bc22eaf5c15bbbded021e7baea93ece832257df1a4b6125fcfa38c35da05dee86aad28d46d73fc4e9d4e5a63b5776f4d733c711e30918b40a5691a6b039552e423d70c168571f74ce9b9abb0ecaf47fcc6652fe0d07/h/list;15a38634f803584ba8926411d7bee906856cab0654b5bd.m3u8'

print(VidPlayProxy(url=url))