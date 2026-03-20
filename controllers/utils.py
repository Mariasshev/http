import math

class RestPagination:
    @staticmethod
    def paginate(data, page, page_size):
        try:
            page = max(1, int(page))
            page_size = max(1, int(page_size))
        except (ValueError, TypeError):
            page, page_size = 1, 10

        total_items = len(data)
        total_pages = math.ceil(total_items / page_size)

        start = (page - 1) * page_size
        end = start + page_size
        paginated_data = data[start:end]

        has_next = page < total_pages
        has_previous = page > 1

        return {
            "metadata": {
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page,
                "page_size": page_size,
                "has_next": has_next,
                "has_previous": has_previous
            },
            "links": {
                "next": page + 1 if has_next else None,
                "prev": page - 1 if has_previous else None
            },
            "results": paginated_data
        }