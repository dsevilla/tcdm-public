from mrjob.job import MRJob


class MRCountAnswers(MRJob):
    def mapper(self, key: str | None, value: str) -> ...:
        # Esquema-número de campo
        # Id:0, AcceptedAnswerId:1, AnswerCount:2, Body:3, ClosedDate:4, CommentCount:5,
        # CommunityOwnedDate:6, ContentLicense:7, CreationDate:8, FavoriteCount:9,
        # LastActivityDate:10, LastEditDate:11, LastEditorDisplayName:12, LastEditorUserId:13,
        # OwnerDisplayName:14, OwnerUserId:15, ParentId:16, PostTypeId:17, Score:18,
        # Tags:19, Title:20, ViewCount:21
        ...

    def combiner(self, key: int, values: ...) -> ...:
        ...

    def reducer(self, key: int, values: ...) -> ...:
        ...

if __name__ == "__main__":
    MRCountAnswers.run()
