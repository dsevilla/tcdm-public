package cursohadoop.wordcount;

import java.io.IOException;
import java.util.stream.StreamSupport;

import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Reducer;

public class WordCountReducer extends Reducer<Text, LongWritable, Text, LongWritable>
{
    @Override
    public void reduce(Text key, Iterable<LongWritable> values, Context ctxt) throws IOException, InterruptedException
    {
        // Sum the values associated with the key using streams
        long sum = StreamSupport.stream(values.spliterator(), false)
            .mapToLong(LongWritable::get)
            .reduce(0, Long::sum);

        ctxt.write(key, new LongWritable(sum));
    }
}
